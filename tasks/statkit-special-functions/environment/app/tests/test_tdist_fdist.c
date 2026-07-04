/* Milestone 2 acceptance: Student's t and F distribution CDFs. */
#include "statkit/distrib.h"
#include "runner.h"

int main(void)
{
    printf("test_tdist_fdist\n");

    /* t CDF at 0 is 1/2 for any nu. */
    for (double nu = 1.0; nu <= 50.0; nu += 5.0) {
        SK_CLOSE(sk_tdist_cdf(0.0, nu), 0.5, 1e-12);
    }

    /* Symmetry: CDF(-t) = 1 - CDF(t); CDF + SF = 1. */
    for (double nu = 1.0; nu <= 40.0; nu += 3.0) {
        for (double t = 0.2; t < 6.0; t += 0.8) {
            SK_CLOSE(sk_tdist_cdf(-t, nu), 1.0 - sk_tdist_cdf(t, nu), 1e-12);
            SK_CLOSE(sk_tdist_cdf(t, nu) + sk_tdist_sf(t, nu), 1.0, 1e-12);
        }
    }

    /* Non-integer degrees of freedom (Welch case) must be supported. */
    SK_CHECK(sk_tdist_cdf(1.5, 10.8) > 0.5 && sk_tdist_cdf(1.5, 10.8) < 1.0);

    /* Known reference values. */
    SK_CLOSE(sk_tdist_cdf(1.0, 5.0), 0.8183912661754386, 1e-9);
    SK_CLOSE(sk_tdist_cdf(2.262157162798205, 9.0), 0.975, 1e-9);

    /* F CDF: positivity, monotonicity, known value. */
    SK_CLOSE(sk_fdist_cdf(0.0, 5.0, 10.0), 0.0, 1e-15);
    SK_CHECK(sk_fdist_cdf(1.0, 5.0, 10.0) < sk_fdist_cdf(4.0, 5.0, 10.0));
    SK_CLOSE(sk_fdist_cdf(3.0, 5.0, 10.0), 0.9344424379061559, 1e-9);

    /* Non-positive degrees of freedom return NaN. */
    SK_CHECK(isnan(sk_tdist_cdf(1.0, 0.0)));
    SK_CHECK(isnan(sk_tdist_cdf(1.0, -3.0)));
    SK_CHECK(isnan(sk_fdist_cdf(2.0, -1.0, 5.0)));
    SK_CHECK(isnan(sk_fdist_cdf(2.0, 5.0, 0.0)));

    SK_DONE();
}
