# Sample spec inputs

These `.spec` files are example inputs for `statctl` (grammar in
`docs/FORMAT.md`). They are inputs only — no expected output is stored here.

* `gof_uniform.spec` — single chi-square goodness-of-fit block.
* `welch_two_sample.spec` — single Welch two-sample t-test, unequal sizes.
* `mixed_suite.spec` — blocks of all three kinds with comments, `ddof`, and
  blank lines interleaved.
* `ks_normality.spec` — two one-sample Kolmogorov-Smirnov normality blocks with
  a non-default `alpha`.

Example:

    build/statctl data/fixtures/mixed_suite.spec -o /tmp/report.json
