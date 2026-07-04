import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


LOG_DIR = Path("/logs/verifier")
RESULTS_PATH = LOG_DIR / "test_results.json"

R_VERIFIER = r"""
DATA <- "/app/environment/data/states"
OUT <- "/app/environment/outputs"
IS_HIDDEN <- identical(Sys.getenv("HIDDEN_VARIANT"), "1")

PANEL_COLUMNS <- c(
  "fips", "state", "county_name", "year", "urbanicity", "region",
  "total_pop_15to64", "total_jail_pop", "total_prison_pop",
  "jail_rate_per_100k", "prison_rate_per_100k"
)
SUMMARY_COLUMNS <- c(
  "urbanicity", "n_county_years", "n_jail_states", "n_prison_states",
  "re_jail_rate_per_100k", "re_prison_rate_per_100k"
)

read_all <- function() {
  files <- sort(list.files(DATA, pattern = "\\.csv$", full.names = TRUE))
  do.call(rbind, lapply(files, function(f)
    read.csv(f, stringsAsFactors = FALSE, colClasses = "character")))
}

rate <- function(count, denom) {
  r <- count / denom * 100000
  r[is.na(count) | is.na(denom) | denom <= 0] <- NA_real_
  round(r, 1)
}

CANON_URBANICITY <- c("rural", "small/mid", "suburban", "urban")

build_reference <- function() {
  dat <- read_all()
  num <- function(x) suppressWarnings(as.numeric(trimws(x)))
  clean_fips <- sprintf("%05d", as.integer(round(num(dat$fips))))
  yr <- as.integer(trimws(dat$year))
  key <- paste(clean_fips, yr)

  ukey <- unique(key)
  firstidx <- match(ukey, key)
  fips_u <- clean_fips[firstidx]
  year_u <- yr[firstidx]

  # Latest non-blank value per county-year, by file order (correction filings).
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

  # Each county's type is the label most frequent across its years; ties resolve
  # toward the canonical order.
  urb_folded <- tolower(trimws(r_urb))
  mode_label <- function(labs) {
    tab <- table(labs)
    top <- names(tab)[tab == max(tab)]
    top[order(match(top, CANON_URBANICITY))][1]
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
  panel <- full[order(full$fips, full$year), ]
  rownames(panel) <- NULL

  groups <- sort(unique(panel$urbanicity))
  weight <- as.integer(panel$total_pop_15to64)
  MIN_YEARS <- 3L
  study_stats <- function(x, w) {
    W <- sum(w)
    y <- sum(w * x) / W
    S2 <- sum(w * (x - y)^2) / W
    list(y = y, v = S2 / length(x), S2 = S2)
  }
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
    m <- panel$urbanicity == g
    dlpool(panel$jail_rate_per_100k[m], weight[m], panel$state[m])
  })
  prison_fit <- lapply(groups, function(g) {
    m <- panel$urbanicity == g
    dlpool(panel$prison_rate_per_100k[m], weight[m], panel$state[m])
  })
  r2 <- function(x) if (is.na(x)) NA_real_ else round(x, 2)
  summ <- data.frame(
    urbanicity = groups,
    n_county_years = as.integer(sapply(groups, function(g) sum(panel$urbanicity == g))),
    n_jail_states = as.integer(sapply(jail_fit, function(f) f$k)),
    n_prison_states = as.integer(sapply(prison_fit, function(f) f$k)),
    re_jail_rate_per_100k = sapply(jail_fit, function(f) r2(f$rate)),
    re_prison_rate_per_100k = sapply(prison_fit, function(f) r2(f$rate)),
    stringsAsFactors = FALSE
  )
  rownames(summ) <- NULL

  # Lever-activity metrics for the public floor guards.
  first_jail <- trimws(dat$total_jail_pop[firstidx])
  n_rec_active <- sum(first_jail != trimws(r_jail))
  n_urb_active <- sum(urb_folded != urb_final)

  list(panel = panel, summ = summ,
       n_rec_active = n_rec_active, n_urb_active = n_urb_active)
}

results <- list()
record <- function(name, ok, messages = NULL) {
  results[[length(results) + 1]] <<- list(
    test = name, status = if (ok) "PASS" else "FAIL", messages = messages)
}
check <- function(name, expr) {
  err <- tryCatch({ force(expr); NULL }, error = function(e) conditionMessage(e))
  record(name, is.null(err), if (is.null(err)) NULL else c(err))
}
fail <- function(message) stop(message, call. = FALSE)
expect_true <- function(x, message = "expected TRUE") if (!isTRUE(x)) fail(message)
same_num <- function(a, b, tol = 1e-6) {
  all((is.na(a) & is.na(b)) | (!is.na(a) & !is.na(b) & abs(a - b) < tol))
}
nonneg_or_na <- function(x) all(is.na(x) | x >= 0)

read_panel <- function() {
  read.csv(file.path(OUT, "county_year_clean.csv"), stringsAsFactors = FALSE,
           na.strings = c("NA", ""),
           colClasses = c(fips = "character", state = "character",
                          county_name = "character", urbanicity = "character",
                          region = "character"))
}
read_urb <- function() {
  read.csv(file.path(OUT, "urbanicity_summary.csv"), stringsAsFactors = FALSE,
           na.strings = c("NA", ""), colClasses = c(urbanicity = "character"))
}

ref <- build_reference()

check("A1 required output files exist", {
  needed <- c("county_year_clean.csv", "urbanicity_summary.csv")
  missing <- needed[!file.exists(file.path(OUT, needed))]
  expect_true(length(missing) == 0, paste("missing:", paste(missing, collapse = ", ")))
})

check("B1 panel has required columns in order", {
  p <- read_panel()
  expect_true(identical(names(p), PANEL_COLUMNS),
              paste("columns:", paste(names(p), collapse = ", ")))
})

check("B2 summary has required columns in order", {
  q <- read_urb()
  expect_true(identical(names(q), SUMMARY_COLUMNS),
              paste("columns:", paste(names(q), collapse = ", ")))
})

check("B3 fips is five digit zero padded", {
  p <- read_panel()
  expect_true(all(grepl("^[0-9]{5}$", p$fips)), "fips not all five digit strings")
})

check("B4 state is a two letter code", {
  p <- read_panel()
  expect_true(all(grepl("^[A-Z]{2}$", p$state)), "state not two letter")
})

check("B5 urbanicity is a single canonical label per category", {
  p <- read_panel()
  bad <- setdiff(unique(p$urbanicity), CANON_URBANICITY)
  expect_true(length(bad) == 0,
              paste("non-canonical urbanicity labels:", paste(bad, collapse = ", ")))
})

check("B6 panel holds one row per county and year", {
  p <- read_panel()
  dup <- sum(duplicated(paste(p$fips, p$year)))
  expect_true(dup == 0, sprintf("%d duplicate county-year rows", dup))
})

check("C1 panel values are well formed", {
  p <- read_panel()
  expect_true(all(p$total_pop_15to64 >= 0), "working-age pop negative")
  expect_true(nonneg_or_na(p$total_jail_pop), "jail pop not nonneg-or-na")
  expect_true(nonneg_or_na(p$total_prison_pop), "prison pop not nonneg-or-na")
  expect_true(nonneg_or_na(p$jail_rate_per_100k), "jail rate not nonneg-or-na")
  expect_true(nonneg_or_na(p$prison_rate_per_100k), "prison rate not nonneg-or-na")
  expect_true(all(is.finite(p$jail_rate_per_100k) | is.na(p$jail_rate_per_100k)),
              "jail rate has non-finite values")
})

check("C2 summary values are well formed", {
  q <- read_urb()
  expect_true(all(q$n_county_years >= 1), "n_county_years below one")
  expect_true(all(q$n_jail_states >= 0 & q$n_jail_states <= q$n_county_years),
              "n_jail_states out of range")
  expect_true(all(q$n_prison_states >= 0 & q$n_prison_states <= q$n_county_years),
              "n_prison_states out of range")
  expect_true(nonneg_or_na(q$re_jail_rate_per_100k), "re jail rate")
  expect_true(nonneg_or_na(q$re_prison_rate_per_100k), "re prison rate")
  expect_true(all(is.na(q$re_jail_rate_per_100k) == (q$n_jail_states == 0)),
              "re jail blank must align with zero states")
  expect_true(all(is.na(q$re_prison_rate_per_100k) == (q$n_prison_states == 0)),
              "re prison blank must align with zero states")
})

check("D1 county panel matches recomputation", {
  p <- read_panel()
  r <- ref$panel
  expect_true(nrow(p) == nrow(r), sprintf("rows %d != %d", nrow(p), nrow(r)))
  expect_true(identical(p$fips, r$fips), "fips differ")
  expect_true(identical(p$state, r$state), "state differ")
  expect_true(identical(p$county_name, r$county_name), "county_name differ")
  expect_true(all(as.integer(p$year) == r$year), "year differ")
  expect_true(identical(p$urbanicity, r$urbanicity), "urbanicity differ")
  expect_true(identical(p$region, r$region), "region differ")
  expect_true(same_num(p$total_pop_15to64, r$total_pop_15to64), "wa pop")
  expect_true(same_num(p$total_jail_pop, r$total_jail_pop), "jail pop")
  expect_true(same_num(p$total_prison_pop, r$total_prison_pop), "prison pop")
  expect_true(same_num(p$jail_rate_per_100k, r$jail_rate_per_100k), "jail rate")
  expect_true(same_num(p$prison_rate_per_100k, r$prison_rate_per_100k), "prison rate")
})

check("D2 urbanicity summary matches recomputation", {
  q <- read_urb()
  r <- ref$summ
  expect_true(nrow(q) == nrow(r), sprintf("rows %d != %d", nrow(q), nrow(r)))
  expect_true(identical(q$urbanicity, r$urbanicity), "urbanicity differ")
  expect_true(all(as.integer(q$n_county_years) == r$n_county_years), "n_county_years")
  expect_true(all(as.integer(q$n_jail_states) == r$n_jail_states), "n_jail_states")
  expect_true(all(as.integer(q$n_prison_states) == r$n_prison_states), "n_prison_states")
  expect_true(same_num(q$re_jail_rate_per_100k, r$re_jail_rate_per_100k))
  expect_true(same_num(q$re_prison_rate_per_100k, r$re_prison_rate_per_100k))
})

check("E1 outputs are internally consistent", {
  p <- read_panel()
  q <- read_urb()
  expect_true(sum(as.integer(q$n_county_years)) == nrow(p),
              "summary counts do not sum to panel rows")
  for (g in q$urbanicity) {
    expect_true(sum(p$urbanicity == g) == q$n_county_years[q$urbanicity == g],
                paste("count mismatch for", g))
  }
})

if (!IS_HIDDEN) {
  check("G1 correction-filing reconciliation is load bearing", {
    expect_true(ref$n_rec_active >= 1000,
                sprintf("only %d county-years diverge from keep-first", ref$n_rec_active))
  })
  check("G2 per-county urbanicity mode is load bearing", {
    expect_true(ref$n_urb_active >= 300,
                sprintf("only %d rows changed by county mode", ref$n_urb_active))
  })
  check("H1 public data lands on known values", {
    p <- read_panel()
    expect_true(nrow(p) == 147533, "n_input_rows")
    expect_true(length(unique(p$state)) == 51, "n_states")
    expect_true(length(unique(p$year)) == 47, "n_years")
    expect_true(min(p$year) == 1970, "first_year")
    expect_true(max(p$year) == 2016, "last_year")
    expect_true(length(unique(p$fips)) == 3139, "n_counties")
    expect_true(sum(!is.na(p$total_jail_pop)) == 141234, "n_jail_present")
    expect_true(sum(!is.na(p$total_prison_pop)) == 80817, "n_prison_present")
  })
  check("H2 analysis does not embed the public answers", {
    f <- "/app/environment/analysis.R"
    src <- paste(readLines(f, warn = FALSE), collapse = "\n")
    expect_true(!grepl("147533", src, fixed = TRUE), "embeds n_input_rows")
    expect_true(!grepl("141234", src, fixed = TRUE), "embeds n_jail_present")
    expect_true(!grepl("80817", src, fixed = TRUE), "embeds n_prison_present")
  })
}

escape_json <- function(x) {
  x <- gsub("\\\\", "\\\\\\\\", x)
  x <- gsub("\"", "\\\\\"", x)
  x <- gsub("\n", "\\\\n", x)
  paste0("\"", x, "\"")
}
entry_json <- function(entry) {
  if (is.null(entry$messages)) {
    msg <- "null"
  } else {
    body <- paste(vapply(entry$messages, escape_json, character(1)), collapse = ",")
    msg <- paste0("[", body, "]")
  }
  paste0("{\"test\":", escape_json(entry$test),
         ",\"status\":", escape_json(entry$status),
         ",\"messages\":", msg, "}")
}
n_pass <- sum(vapply(results, function(x) identical(x$status, "PASS"), logical(1)))
n_fail <- length(results) - n_pass
dir.create("/logs/verifier", showWarnings = FALSE, recursive = TRUE)
json <- paste0(
  "{\"summary\":{\"passed\":", n_pass, ",\"failed\":", n_fail, "},\"tests\":[",
  paste(vapply(results, entry_json, character(1)), collapse = ","), "]}")
writeLines(json, "/logs/verifier/test_results.json")

if (n_fail > 0) quit(status = 1)
quit(status = 0)
"""


def _run_r(script):
    kwargs = {"suffix": ".R", "delete": False, "encoding": "utf-8"}
    with tempfile.NamedTemporaryFile("w", **kwargs) as handle:
        handle.write(script)
        path = handle.name
    try:
        return subprocess.run(
            ["Rscript", path],
            check=False,
            capture_output=True,
            text=True,
            timeout=1100,
            env=os.environ.copy(),
        )
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.fixture(scope="session")
def r_results():
    """Run the embedded R verifier once per pytest process and expose its per-check results.

    The R side records every check (A1, B1-B6, C1-C2, D1-D2, E1, H1-H2) into
    test_results.json before exiting, so each pytest function below can assert
    on its own check and partial credit stays visible in the pytest report.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if RESULTS_PATH.exists():
        RESULTS_PATH.unlink()
    completed = _run_r(R_VERIFIER)
    results = {}
    if RESULTS_PATH.exists():
        try:
            data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
            for item in data.get("tests", []):
                key = str(item.get("test", "")).split(" ", 1)[0]
                if key:
                    results[key] = item
        except json.JSONDecodeError:
            pass
    return {"completed": completed, "results": results}


IS_HIDDEN = os.environ.get("HIDDEN_VARIANT") == "1"
PUBLIC_ONLY = {"G1", "G2", "H1", "H2"}


def _assert_check(r_results, check_id):
    results = r_results["results"]
    if check_id not in results:
        if check_id in PUBLIC_ONLY and IS_HIDDEN:
            pytest.skip(f"{check_id} runs on the public pass only")
        completed = r_results["completed"]
        detail = (completed.stderr or completed.stdout or "").strip()
        raise AssertionError(
            f"R verifier did not record {check_id} (returncode "
            f"{completed.returncode}). R output:\n{detail}"
        )
    item = results[check_id]
    if item.get("status") != "PASS":
        messages = "; ".join(str(m) for m in (item.get("messages") or []))
        name = item.get("test", check_id)
        raise AssertionError(f"{name}: {messages}" if messages else name)


def test_output_files_exist(r_results):
    """A1: both output CSVs are present."""
    _assert_check(r_results, "A1")


def test_panel_columns(r_results):
    """B1: the panel has the required columns in the required order."""
    _assert_check(r_results, "B1")


def test_summary_columns(r_results):
    """B2: the summary has the required columns in the required order."""
    _assert_check(r_results, "B2")


def test_fips_format(r_results):
    """B3: fips is a five digit zero padded string."""
    _assert_check(r_results, "B3")


def test_state_format(r_results):
    """B4: state is a two letter code."""
    _assert_check(r_results, "B4")


def test_urbanicity_canonical(r_results):
    """B5: urbanicity is a single canonical label per category."""
    _assert_check(r_results, "B5")


def test_one_row_per_county_year(r_results):
    """B6: the panel holds one row per county and year."""
    _assert_check(r_results, "B6")


def test_panel_values_wellformed(r_results):
    """C1: panel populations and rates are non-negative or blank."""
    _assert_check(r_results, "C1")


def test_summary_values_wellformed(r_results):
    """C2: summary counts and mean rates are well formed."""
    _assert_check(r_results, "C2")


def test_panel_values_match_reference(r_results):
    """D1: the panel matches an independent recomputation from the source."""
    _assert_check(r_results, "D1")


def test_summary_values_match_reference(r_results):
    """D2: the summary matches an independent recomputation from the source."""
    _assert_check(r_results, "D2")


def test_outputs_internally_consistent(r_results):
    """E1: summary group counts sum and align with the panel."""
    _assert_check(r_results, "E1")


def test_reconciliation_lever_active(r_results):
    """G1: correction-filing reconciliation actually changes the public panel."""
    _assert_check(r_results, "G1")


def test_urbanicity_mode_lever_active(r_results):
    """G2: per-county urbanicity majority resolution changes the public panel."""
    _assert_check(r_results, "G2")


def test_public_known_values(r_results):
    """H1: the public panel lands on the known corpus totals."""
    _assert_check(r_results, "H1")


def test_no_embedded_answers(r_results):
    """H2: the analysis does not hard code the public answers."""
    _assert_check(r_results, "H2")
