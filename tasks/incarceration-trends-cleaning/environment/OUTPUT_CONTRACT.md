# Output contract

`analysis.R` reads the per-state CSV files under `/app/environment/data/states`
and writes two files into `/app/environment/outputs`, which is cleared on every
run. Use only the columns `year`, `fips`, `state`, `county_name`, `urbanicity`,
`region`, `total_pop_15to64` (the working age population, ages 15 through 64),
`total_jail_pop`, and `total_prison_pop`; ignore any others.

## Reconciling the repeated rows

A county and year often appears on more than one row: a later row is a
correction that fills in or overrides some fields and leaves the rest blank, so
no single row is complete. Collapse each county and year to one record. For
every field, take the value from the latest row, in the order the rows appear
in the file, that is not blank; a blank in a later row never erases a value an
earlier row supplied. A field is blank only when no row for that county and
year fills it.

## Resolving urbanicity

A county's urbanicity is recorded inconsistently across its years, sometimes
only in casing or spacing and sometimes as a different type label. Give each
county the single label that appears most often among its reconciled rows once
case and surrounding spaces are ignored, breaking ties toward the order
`rural`, `small/mid`, `suburban`, `urban`. Apply that one lower case label to
every one of the county's rows. Every county type resolves to exactly one of
`rural`, `small/mid`, `suburban`, and `urban`.

## `county_year_clean.csv`

One row per county and year, with these columns in this order:

`fips`, `state`, `county_name`, `year`, `urbanicity`, `region`,
`total_pop_15to64`, `total_jail_pop`, `total_prison_pop`, `jail_rate_per_100k`,
`prison_rate_per_100k`.

- `fips` is the five character zero padded county identifier as text.
- `total_jail_pop` and `total_prison_pop` carry through as whole numbers
  truncated toward zero, blank where the reconciled record had no count.
- Each rate is the reconciled count per 100,000 working age residents, computed
  from the raw count including any fractional part, and blank when the count is
  missing or the working age population is not positive.
- Sort by `fips` then `year`.

## `urbanicity_summary.csv`

One row per canonical label, with these columns in this order: `urbanicity`,
`n_county_years`, `n_jail_states`, `n_prison_states`, `re_jail_rate_per_100k`,
`re_prison_rate_per_100k`. Sort by `urbanicity`.

- `n_county_years` counts the cleaned panel rows in that group.

The two `re` columns report a typical rate for the group that treats each state
as one observation and accounts for how much the states disagree, rather than
letting the largest counties dominate a plain population weighted mean. Compute
each one, separately for the jail rate and the prison rate, as a
DerSimonian and Laird random effects pooled estimate over the group's states,
as follows.

First form one study per state. Within the group, take each state's rows whose
rate is present in `county_year_clean.csv` and whose `total_pop_15to64` is
greater than zero, weighting each such row by its `total_pop_15to64` value as
written there and taking its value to be the rate exactly as written, already
rounded to one decimal. A state becomes an included study for that rate only
when it has at least three such rows and their rates are not all equal; states
that do not clear both conditions are left out of that rate's pool. For an
included state with weights `w` and values `x`, its study estimate and study
variance are

- `y = sum(w * x) / sum(w)`, the state's population weighted rate;
- `S2 = sum(w * (x - y)^2) / sum(w)`, its population weighted variance, dividing
  by the total weight, not by the total weight minus one;
- `v = S2 / n`, where `n` is the number of those rows, the study variance, an
  estimate of the squared standard error of `y`.

Let the group have `k` included studies for the rate, with estimates `y_i` and
variances `v_i`. When `k` is zero the pooled rate is blank; when `k` is one the
pooled rate is that single `y`. Otherwise pool them with random effects:

1. Fixed effect weights `a_i = 1 / v_i`, and `ybar = sum(a * y) / sum(a)`.
2. Heterogeneity `Q = sum(a * (y - ybar)^2)` and
   `C = sum(a) - sum(a^2) / sum(a)`.
3. The between study variance `tau2 = max(0, (Q - (k - 1)) / C)`.
4. Random effects weights `b_i = 1 / (v_i + tau2)`, and the pooled rate is
   `sum(b * y) / sum(b)`, rounded to two decimals.

`n_jail_states` and `n_prison_states` are how many state studies were pooled for
the jail rate and the prison rate. The `re` value is blank exactly when the
count is zero.

## Rounding

Round half to even, the behaviour of R's `round()`: panel rates to one decimal,
and each group `re` rate to two decimals, formed from the study estimates that
are themselves built on the already rounded panel rates. Write every number as a
plain decimal, the way `write.csv` does, never in exponential form or padded to a
fixed width; the verifier reads the outputs back as numbers and compares them to
its own recomputation within a small tolerance.
