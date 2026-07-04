#include "statkit/distrib.h"

#include <math.h>

/*
 * Kolmogorov distribution survival function and the normal CDF used as the
 * reference distribution for a one-sample Kolmogorov-Smirnov test.
 *
 * TODO(milestone 4): implement these. See docs/ALGORITHMS.md. The placeholder
 * bodies compile but return a sentinel so the milestone-4 tests fail until the
 * real implementation lands.
 */

double sk_normal_cdf(double x, double mu, double sigma)
{
    (void)x;
    (void)mu;
    (void)sigma;
    return -1.0; /* not implemented */
}

double sk_ks_sf(double t)
{
    (void)t;
    return -1.0; /* not implemented */
}
