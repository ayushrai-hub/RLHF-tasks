# statctl spec format and report schema

`statctl` reads a `.spec` suite, runs each test, and writes a JSON report.

    statctl <spec-path> [-o <output-path>]

`<spec-path>` is required. `-o` overrides the output path; the default is
`/app/output/report.json`. `statctl` exits 0 when the report is written with at
least one valid test, and non-zero when the spec file cannot be opened or the
suite contains no valid test.

## Spec grammar

Plain text, one directive per line. Blank lines and lines whose first
non-space character is `#` are ignored. A test is a block:

    test <id> <kind>
    <key> <value>...
    ...
    end

`<id>` is a short token (letters, digits, `_`, `-`). `<kind>` is `chisq_gof`,
`welch_t`, or `ks_normal`. Keys inside a block:

* `chisq_gof`
  * `observed v1 v2 ...`  observed counts (one or more)
  * `expected v1 v2 ...`  expected counts, same length as `observed`
  * `ddof k`              optional integer, default 0
* `welch_t`
  * `sample_a v1 v2 ...`  first sample (two or more values)
  * `sample_b v1 v2 ...`  second sample (two or more values)
* `ks_normal`
  * `sample v1 v2 ...`    sample to test for normality (two or more values)
  * `mu m`                mean of the reference normal
  * `sigma s`             standard deviation of the reference normal (> 0)

A top-level directive `alpha <value>` (outside any block) sets the suite
significance level used for the multiple-testing decision and the intervals
below; it defaults to `0.05` if absent.

Tests appear in the report in the same order they appear in the file.

A block is **malformed** and must be skipped (the rest of the suite still runs)
when: `observed` and `expected` differ in length, any `expected` value is not
strictly positive, a sample has fewer than two values, `sigma` is not strictly
positive, or a required key is missing. If skipping leaves no valid tests,
`statctl` exits non-zero.

## Test definitions

### chisq_gof

Pearson goodness-of-fit over `m` categories:

    statistic = sum_i (observed_i - expected_i)^2 / expected_i
    df        = m - 1 - ddof
    pvalue    = upper-tail chi-square survival at `df`  (sk_chisq_sf)

### welch_t

Two-sample t-test that does **not** assume equal variances. With sample means
`ma, mb`, unbiased variances `va, vb`, and sizes `na, nb`:

    statistic = (ma - mb) / sqrt(va/na + vb/nb)

    df = (va/na + vb/nb)^2
         / ( (va/na)^2 / (na - 1) + (vb/nb)^2 / (nb - 1) )      (Welch-Satterthwaite)

`df` is generally **not** an integer. The reported `pvalue` is two-sided:

    pvalue = 2 * (1 - F_t(|statistic|; df))

### ks_normal

One-sample Kolmogorov-Smirnov test of the `sample` against the normal
distribution `N(mu, sigma)`. With the sample sorted ascending as
`x_(1) <= ... <= x_(n)` and `F` the reference normal CDF:

    Dplus     = max over i of ( i/n     - F(x_(i)) )
    Dminus    = max over i of ( F(x_(i)) - (i-1)/n )
    statistic = D = max(Dplus, Dminus)
    pvalue    = sk_ks_sf( sqrt(n) * D )

(`i` runs from 1 to n.) A `ks_normal` entry has no `df`.

## Per-test extras

In addition to the raw `pvalue`, each valid test reports:

* `critical_value` (chisq_gof only): the rejection threshold for the statistic,
  i.e. the chi-square quantile `sk_chisq_ppf(1 - alpha, df)`.
* `ci_low`, `ci_high` (welch_t only): a two-sided confidence interval for the
  mean difference `(ma - mb)` at level `1 - alpha`:

      half = sk_tdist_ppf(1 - alpha/2, df) * sqrt(va/na + vb/nb)
      ci_low  = (ma - mb) - half
      ci_high = (ma - mb) + half

A `ks_normal` entry carries no extra field beyond the common ones below.

## Multiple-testing correction (Holm-Bonferroni)

The raw p-values of all valid tests are adjusted together with the
Holm-Bonferroni step-down procedure, using only the `m` valid tests. Sort the
raw p-values ascending as `p_(1) <= ... <= p_(m)`. The adjusted value at sorted
rank `j` (1-based) is

    a_(j) = max over i <= j of  min(1, (m - i + 1) * p_(i))

(the running maximum enforces monotonicity, and each term is capped at 1). Each
test's `adj_pvalue` is `a` mapped back to its original position, and `reject` is
`true` when `adj_pvalue <= alpha`, else `false`.

## Report schema

A single minified JSON object on one line, followed by exactly one trailing
newline. No insignificant whitespace.

    {"version":1,"alpha":<num>,"tests":[
       {"id":"<id>","kind":"chisq_gof","statistic":<num>,"df":<num>,"pvalue":<num>,
        "adj_pvalue":<num>,"reject":<bool>,"critical_value":<num>},
       {"id":"<id>","kind":"welch_t","statistic":<num>,"df":<num>,"pvalue":<num>,
        "adj_pvalue":<num>,"reject":<bool>,"ci_low":<num>,"ci_high":<num>},
       {"id":"<id>","kind":"ks_normal","statistic":<num>,"pvalue":<num>,
        "adj_pvalue":<num>,"reject":<bool>}
    ]}

(shown wrapped for readability; the real file is one line). `version` is the
report schema version (1). `alpha` is the suite significance level. `reject` is
a JSON boolean (`true`/`false`); all other values are plain JSON numbers. A
`chisq_gof` entry carries `df` and `critical_value`; a `welch_t` entry carries
`df`, `ci_low`, and `ci_high`; a `ks_normal` entry carries neither `df` nor any
extra field.
