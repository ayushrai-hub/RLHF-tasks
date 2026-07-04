#include "statkit/distrib.h"

#include <math.h>

/*
 * Inverse CDFs (quantiles) for the chi-square and Student-t distributions.
 *
 * TODO(milestone 3): implement these as the inverses of sk_chisq_cdf and
 * sk_tdist_cdf (docs/ALGORITHMS.md). The placeholder bodies compile but return
 * a sentinel so the milestone-3 tests fail until the real implementation lands.
 */

double sk_chisq_ppf(double p, double k)
{
    (void)p;
    (void)k;
    return -1.0; /* not implemented */
}

double sk_tdist_ppf(double p, double nu)
{
    (void)p;
    (void)nu;
    return -1.0; /* not implemented */
}
