Next stage of the statkit library at `/app`. The CDFs and quantiles from before should stay intact.

Add the pieces a one-sample Kolmogorov-Smirnov normality test needs. Implement `sk_normal_cdf` (the normal CDF, used as the reference distribution) and `sk_ks_sf` (the survival function of the asymptotic Kolmogorov distribution of the K-S statistic) in `/app/src/ksdist.c`. Definitions and the accuracy targets are in `/app/docs/ALGORITHMS.md`; `sk_ks_sf` should be 1 at and below 0 and fall to 0 as its argument grows, and `sk_normal_cdf` should return NaN for a non-positive standard deviation.

The frozen check for this stage is `/app/tests/test_ksdist.c`. Build from `/app` with `make`. Leave the headers, `/app/tests`, and `/app/data` alone, and keep `statctl` stubbed — the CLI is the last stage.
