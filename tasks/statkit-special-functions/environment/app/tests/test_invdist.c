/* Milestone 3 acceptance: inverse CDFs (quantiles) for chi-square and t. */
#include "statkit/distrib.h"
#include "runner.h"

int main(void)
{
    printf("test_invdist\n");

    /* Round trip: F(ppf(p)) == p across a range of p and df. */
    for (double k = 1.0; k <= 30.0; k += 4.0) {
        for (double p = 0.05; p < 1.0; p += 0.1) {
            double x = sk_chisq_ppf(p, k);
            SK_CLOSE(sk_chisq_cdf(x, k), p, 1e-6);
        }
    }
    for (double nu = 1.0; nu <= 40.0; nu += 6.0) {
        for (double p = 0.05; p < 1.0; p += 0.1) {
            double t = sk_tdist_ppf(p, nu);
            SK_CLOSE(sk_tdist_cdf(t, nu), p, 1e-6);
        }
    }

    /* Symmetry and a fixed point for the t quantile. */
    SK_CLOSE(sk_tdist_ppf(0.5, 7.0), 0.0, 1e-6);
    SK_CLOSE(sk_tdist_ppf(0.25, 7.0), -sk_tdist_ppf(0.75, 7.0), 1e-6);

    /* Monotonic in p. */
    SK_CHECK(sk_chisq_ppf(0.3, 8.0) < sk_chisq_ppf(0.7, 8.0));
    SK_CHECK(sk_tdist_ppf(0.3, 8.0) < sk_tdist_ppf(0.7, 8.0));

    /* Non-integer degrees of freedom must work. */
    SK_CHECK(sk_tdist_ppf(0.9, 10.86) > 0.0);

    /* Known reference quantiles. */
    SK_CLOSE(sk_chisq_ppf(0.95, 10.0), 18.307038053275146, 1e-4);
    SK_CLOSE(sk_tdist_ppf(0.975, 9.0), 2.262157162798205, 1e-4);

    /* Domain errors return NaN. */
    SK_CHECK(isnan(sk_chisq_ppf(0.0, 10.0)));
    SK_CHECK(isnan(sk_chisq_ppf(1.0, 10.0)));
    SK_CHECK(isnan(sk_chisq_ppf(0.5, 0.0)));
    SK_CHECK(isnan(sk_tdist_ppf(-0.1, 9.0)));
    SK_CHECK(isnan(sk_tdist_ppf(0.5, -2.0)));

    SK_DONE();
}
