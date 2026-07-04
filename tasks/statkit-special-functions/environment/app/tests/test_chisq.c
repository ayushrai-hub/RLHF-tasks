/* Milestone 1 acceptance: chi-square CDF / survival function. */
#include "statkit/distrib.h"
#include "runner.h"

int main(void)
{
    printf("test_chisq\n");

    /* Closed form for k = 2: CDF(x) = 1 - e^{-x/2}. */
    for (double x = 0.3; x < 14.0; x += 0.7) {
        SK_CLOSE(sk_chisq_cdf(x, 2.0), 1.0 - exp(-x / 2.0), 1e-12);
    }

    /* CDF + SF = 1. */
    for (double k = 1.0; k <= 20.0; k += 1.0) {
        for (double x = 0.5; x < 30.0; x += 2.5) {
            SK_CLOSE(sk_chisq_cdf(x, k) + sk_chisq_sf(x, k), 1.0, 1e-12);
        }
    }

    /* Left boundary. */
    SK_CLOSE(sk_chisq_cdf(0.0, 5.0), 0.0, 1e-15);
    SK_CLOSE(sk_chisq_sf(0.0, 5.0), 1.0, 1e-15);

    /* Known reference values. */
    SK_CLOSE(sk_chisq_cdf(18.307038053275146, 10.0), 0.95, 1e-9);
    SK_CLOSE(sk_chisq_sf(2.9, 4.0), 0.5746972058298043, 1e-9);

    /* Non-positive degrees of freedom return NaN. */
    SK_CHECK(isnan(sk_chisq_cdf(5.0, 0.0)));
    SK_CHECK(isnan(sk_chisq_cdf(5.0, -2.0)));
    SK_CHECK(isnan(sk_chisq_sf(5.0, -1.0)));

    SK_DONE();
}
