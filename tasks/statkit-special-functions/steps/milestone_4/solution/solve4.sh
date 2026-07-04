#!/bin/bash
# Oracle solution scoped to milestone 4 only:
# the normal CDF and the Kolmogorov survival function for a K-S test.
set -euo pipefail
cd /app

cat > src/ksdist.c <<'EOF'
#include "statkit/distrib.h"

#include <math.h>

double sk_normal_cdf(double x, double mu, double sigma)
{
    if (sigma <= 0.0) {
        return NAN;
    }
    return 0.5 * erfc(-(x - mu) / (sigma * sqrt(2.0)));
}

/* Asymptotic Kolmogorov survival function. The alternating series is summed
   directly; for small t the terms decay slowly and the clamped partial sum
   tends to 1, which is the correct limit. */
double sk_ks_sf(double t)
{
    if (t <= 0.0) {
        return 1.0;
    }
    double s = 0.0;
    double sign = 1.0;
    double a2 = -2.0 * t * t;
    for (int k = 1; k < 1000; ++k) {
        double term = sign * exp(a2 * (double)k * (double)k);
        s += term;
        sign = -sign;
        if (fabs(term) < 1e-18) {
            break;
        }
    }
    double v = 2.0 * s;
    if (v < 0.0) {
        v = 0.0;
    }
    if (v > 1.0) {
        v = 1.0;
    }
    return v;
}
EOF

make lib
make build/test/test_ksdist
build/test/test_ksdist
