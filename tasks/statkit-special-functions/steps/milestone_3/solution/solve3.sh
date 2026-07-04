#!/bin/bash
# Oracle solution scoped to milestone 3 only:
# inverse CDFs (quantiles) for the chi-square and Student-t distributions.
set -euo pipefail
cd /app

cat > src/invdist.c <<'EOF'
#include "statkit/distrib.h"

#include <math.h>

/* Quantile = inverse CDF, found by bracketing then bisection. The CDFs are
   continuous and strictly increasing in their argument, so bisection converges. */

double sk_chisq_ppf(double p, double k)
{
    if (p <= 0.0 || p >= 1.0 || k <= 0.0) {
        return NAN;
    }
    double lo = 0.0;
    double hi = 1.0;
    while (sk_chisq_cdf(hi, k) < p) {
        hi *= 2.0;
        if (hi > 1e15) {
            break;
        }
    }
    for (int i = 0; i < 200; ++i) {
        double mid = 0.5 * (lo + hi);
        if (sk_chisq_cdf(mid, k) < p) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    return 0.5 * (lo + hi);
}

double sk_tdist_ppf(double p, double nu)
{
    if (p <= 0.0 || p >= 1.0 || nu <= 0.0) {
        return NAN;
    }
    double lo = -1.0;
    double hi = 1.0;
    while (sk_tdist_cdf(lo, nu) > p) {
        lo *= 2.0;
        if (lo < -1e15) {
            break;
        }
    }
    while (sk_tdist_cdf(hi, nu) < p) {
        hi *= 2.0;
        if (hi > 1e15) {
            break;
        }
    }
    for (int i = 0; i < 200; ++i) {
        double mid = 0.5 * (lo + hi);
        if (sk_tdist_cdf(mid, nu) < p) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    return 0.5 * (lo + hi);
}
EOF

make lib
make build/test/test_invdist
build/test/test_invdist
