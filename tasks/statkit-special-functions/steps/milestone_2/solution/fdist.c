#include "statkit/distrib.h"
#include "statkit/specfun.h"

#include <math.h>

double sk_fdist_cdf(double f, double d1, double d2)
{
    if (d1 <= 0.0 || d2 <= 0.0) {
        return NAN;
    }
    if (f <= 0.0) {
        return 0.0;
    }
    double w = d1 * f / (d1 * f + d2);
    return sk_betai(d1 / 2.0, d2 / 2.0, w);
}
