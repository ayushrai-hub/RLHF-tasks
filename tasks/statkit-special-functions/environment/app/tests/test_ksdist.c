/* Milestone 4 acceptance: normal CDF + Kolmogorov survival function. */
#include "statkit/distrib.h"
#include "runner.h"

int main(void)
{
    printf("test_ksdist\n");

    /* Normal CDF: standard reference points and symmetry. */
    SK_CLOSE(sk_normal_cdf(0.0, 0.0, 1.0), 0.5, 1e-12);
    SK_CLOSE(sk_normal_cdf(1.0, 0.0, 1.0), 0.8413447460685428, 1e-10);
    SK_CLOSE(sk_normal_cdf(1.96, 0.0, 1.0), 0.9750021048517796, 1e-10);
    SK_CLOSE(sk_normal_cdf(3.0, 5.0, 2.0), 0.15865525393145707, 1e-10);
    for (double z = -3.0; z <= 3.0; z += 0.5) {
        SK_CLOSE(sk_normal_cdf(z, 0.0, 1.0) + sk_normal_cdf(-z, 0.0, 1.0), 1.0, 1e-12);
    }
    SK_CHECK(isnan(sk_normal_cdf(1.0, 0.0, 0.0)));
    SK_CHECK(isnan(sk_normal_cdf(1.0, 0.0, -2.0)));

    /* Kolmogorov survival function: boundary, monotonicity, known values. */
    SK_CLOSE(sk_ks_sf(-1.0), 1.0, 1e-12);
    SK_CLOSE(sk_ks_sf(0.0), 1.0, 1e-12);
    SK_CLOSE(sk_ks_sf(0.5), 0.9639452436648751, 1e-7);
    SK_CLOSE(sk_ks_sf(1.0), 0.26999967167735456, 1e-7);
    SK_CLOSE(sk_ks_sf(2.0), 0.0006709252557796953, 1e-9);
    SK_CHECK(sk_ks_sf(0.5) > sk_ks_sf(1.0));
    SK_CHECK(sk_ks_sf(1.0) > sk_ks_sf(2.0));
    SK_CHECK(sk_ks_sf(0.05) > 0.999);

    SK_DONE();
}
