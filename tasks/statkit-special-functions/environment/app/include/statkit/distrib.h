#ifndef STATKIT_DISTRIB_H
#define STATKIT_DISTRIB_H

/*
 * Cumulative distribution functions built on top of the special functions in
 * specfun.h. Relationships between each distribution and the incomplete
 * gamma/beta functions are given in docs/ALGORITHMS.md.
 *
 * Degrees of freedom are passed as doubles: the Welch two-sample test produces
 * a non-integer degrees-of-freedom value, so every df parameter here is real.
 *
 * Each function returns NaN when a degrees-of-freedom argument is not strictly
 * positive (k <= 0, nu <= 0, d1 <= 0, or d2 <= 0).
 */

/* Chi-square CDF and survival function (upper tail), k > 0 degrees of freedom. */
double sk_chisq_cdf(double x, double k);
double sk_chisq_sf(double x, double k);

/* Student's t CDF and survival function, nu > 0 degrees of freedom. */
double sk_tdist_cdf(double t, double nu);
double sk_tdist_sf(double t, double nu);

/* F-distribution CDF, d1 > 0 and d2 > 0 degrees of freedom. */
double sk_fdist_cdf(double f, double d1, double d2);

/*
 * Inverse CDFs (quantile functions): given a probability p in the open
 * interval (0, 1), return the value whose CDF equals p. They are the inverses
 * of sk_chisq_cdf and sk_tdist_cdf respectively. Return NaN when p is outside
 * (0, 1) or a degrees-of-freedom argument is not strictly positive.
 */
double sk_chisq_ppf(double p, double k);
double sk_tdist_ppf(double p, double nu);

/*
 * Normal CDF for the reference distribution of a one-sample test.
 * sigma must be > 0; returns NaN otherwise.
 */
double sk_normal_cdf(double x, double mu, double sigma);

/*
 * Survival function of the asymptotic (Kolmogorov) distribution of the
 * one-sample Kolmogorov-Smirnov statistic: Q(t) = P(sqrt(n) * D > t) in the
 * large-sample limit. Q(t) = 1 for t <= 0 and decreases to 0 as t grows.
 * See docs/ALGORITHMS.md.
 */
double sk_ks_sf(double t);

#endif /* STATKIT_DISTRIB_H */
