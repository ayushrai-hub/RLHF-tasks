#include "statkit/distrib.h"
#include "statkit/specfun.h"

#include <math.h>

double sk_chisq_cdf(double x, double k)
{
    if (k <= 0.0) {
        return NAN;
    }
    if (x <= 0.0) {
        return 0.0;
    }
    return sk_gammap(k / 2.0, x / 2.0);
}

double sk_chisq_sf(double x, double k)
{
    if (k <= 0.0) {
        return NAN;
    }
    if (x <= 0.0) {
        return 1.0;
    }
    return sk_gammaq(k / 2.0, x / 2.0);
}
